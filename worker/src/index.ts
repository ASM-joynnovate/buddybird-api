import { retryable } from "cloudflare:durable-objects";
import { DurableObject, WorkerEntrypoint } from "cloudflare:workers";

interface Env {
	API: DurableObjectNamespace<Api>;
	API_ROUTER: DurableObjectNamespace<ApiRouter>;
	ENV: string;
	QUEUE_URL: string;
	VERSION: WorkerVersionMetadata;
	PARROT_SOUND_DETECTION_QUEUE: Queue;
	MIMICRY_JUDGMENT_QUEUE: Queue;
	NOTIFICATION_QUEUE: Queue;
	WITHDRAWAL_QUEUE: Queue;
}

declare global {
	namespace Cloudflare {
		interface GlobalProps {
			mainModule: typeof import("./index");
		}
	}
}

type Color = "blue" | "green";

const PORT = 8000;
const INACTIVITY_TIMEOUT_MS = 10 * 60 * 1000;
const READY_ATTEMPTS = 120;
const READY_INTERVAL_MS = 500;
const DRAIN_MS = 30 * 1000;
const HEALTH_ATTEMPTS = 3;
const HEALTH_INTERVAL_MS = 10 * 1000;
const HEALTH_TIMEOUT_MS = 5 * 1000;
const STOP_DEADLINE_MS = 30 * 1000;
const SIGTERM = 15;
const MIGRATION_ENTRYPOINT = ["alembic", "upgrade", "head"];
const DLQ_RETRY_BASE_SECONDS = 30;
const MAX_RETRY_DELAY_SECONDS = 24 * 60 * 60;
const CRON_TASKS = ["withdrawal.dispatch", "session.check_heartbeats", "push.dispatch"];
const LOCATION_HINT = "apac-ne";

function router(env: Env): DurableObjectStub<ApiRouter> {
	return env.API_ROUTER.getByName("router", { locationHint: LOCATION_HINT });
}

function api(env: Env, color: Color): DurableObjectStub<Api> {
	return env.API.getByName(color, { locationHint: LOCATION_HINT });
}

function retryOptions(name: string, attempts: number): QueueRetryOptions | undefined {
	if (!name.endsWith("-dlq")) {
		return undefined;
	}
	return { delaySeconds: Math.min(DLQ_RETRY_BASE_SECONDS * 2 ** (attempts - 1), MAX_RETRY_DELAY_SECONDS) };
}

export class QueuePublisher extends WorkerEntrypoint<Env> {
	async fetch(request: Request): Promise<Response> {
		const queues: Record<string, Queue> = {
			"/parrot-sound-detection": this.env.PARROT_SOUND_DETECTION_QUEUE,
			"/mimicry-judgment": this.env.MIMICRY_JUDGMENT_QUEUE,
			"/notification": this.env.NOTIFICATION_QUEUE,
			"/withdrawal": this.env.WITHDRAWAL_QUEUE,
		};
		const queue = queues[new URL(request.url).pathname];
		if (request.method !== "POST" || queue === undefined) {
			return new Response(null, { status: 404 });
		}
		await queue.send(await request.json());
		return new Response(null, { status: 204 });
	}
}

export class Api extends DurableObject<Env> {
	private starting: Promise<void> | undefined;
	private ready = false;
	private cronRun: Promise<void> | undefined;
	private stopRequested = false;

	constructor(ctx: DurableObjectState, env: Env) {
		super(ctx, env);
		const container = ctx.container!;
		if (container.running) {
			void ctx.blockConcurrencyWhile(() => container.setInactivityTimeout(INACTIVITY_TIMEOUT_MS));
		}
	}

	async fetch(request: Request): Promise<Response> {
		if (this.env.ENV !== "prod") {
			await this.ctx.storage.setAlarm(Date.now() + INACTIVITY_TIMEOUT_MS);
		}
		try {
			await this.ensureReady();
		} catch (error) {
			console.error("api container is not ready", error);
			return new Response(null, { status: 503 });
		}

		const url = new URL(request.url);
		url.protocol = "http:";
		const forwarded = new Request(url, request);
		forwarded.headers.set("X-Forwarded-Proto", "https");
		return this.ctx.container!.getTcpPort(PORT).fetch(forwarded);
	}

	runCron(): Promise<void> {
		this.cronRun ??= this.runCronTasks().finally(() => {
			this.cronRun = undefined;
		});
		return this.cronRun;
	}

	async version(): Promise<string> {
		return (await this.ctx.container!.inspect())?.labels.version ?? "";
	}

	async outdated(version: string): Promise<boolean> {
		const info = await this.ctx.container!.inspect();
		return info !== null && info.image !== "" && info.labels.version !== version;
	}

	async prepare(version: string): Promise<void> {
		if (this.env.VERSION.id !== version) {
			this.ctx.abort(`api object runs version ${this.env.VERSION.id}, not ${version}`);
		}
		await this.stop();
		if (this.env.ENV !== "prod") {
			await this.ctx.storage.setAlarm(Date.now() + INACTIVITY_TIMEOUT_MS);
		}
		await this.ensureReady();
	}

	async alarm(): Promise<void> {
		await this.stop();
	}

	async stop(): Promise<void> {
		const container = this.ctx.container!;
		if (!container.running) {
			return;
		}
		this.stopRequested = true;
		container.signal(SIGTERM);
		await Promise.race([container.monitor().catch(() => undefined), scheduler.wait(STOP_DEADLINE_MS)]);
		if (container.running) {
			await container.destroy("api container did not stop");
		}
	}

	private async runCronTasks(): Promise<void> {
		const container = this.ctx.container!;
		if (this.env.ENV !== "prod" && !container.running) {
			return;
		}
		if (this.ready && container.running && !(await this.healthy())) {
			await this.stop();
		}
		await this.ensureReady();

		const port = container.getTcpPort(PORT);
		const failures: string[] = [];
		for (const task of CRON_TASKS) {
			const response = await port.fetch(`http://container/internal/cron/${task}`, { method: "POST" });
			await response.body?.cancel();
			if (!response.ok) {
				failures.push(`${task} ${response.status}`);
			}
		}
		if (failures.length > 0) {
			throw new Error(`cron tasks failed: ${failures.join(", ")}`);
		}
	}

	private async healthy(): Promise<boolean> {
		const port = this.ctx.container!.getTcpPort(PORT);
		for (let attempt = 0; attempt < HEALTH_ATTEMPTS; attempt++) {
			if (attempt > 0) {
				await scheduler.wait(HEALTH_INTERVAL_MS);
			}
			try {
				const response = await port.fetch("http://container/api/healthz", {
					signal: AbortSignal.timeout(HEALTH_TIMEOUT_MS),
				});
				await response.body?.cancel();
				if (response.status === 200) {
					return true;
				}
			} catch (error) {
				console.error("api health check failed", error);
			}
		}
		return false;
	}

	private async ensureReady(): Promise<void> {
		if (this.ready && this.ctx.container!.running) {
			return;
		}
		this.ready = false;
		this.starting ??= this.start().finally(() => {
			this.starting = undefined;
		});
		await this.starting;
		this.ready = true;
	}

	private async start(): Promise<void> {
		const container = this.ctx.container!;
		const version = this.env.VERSION.id;
		const options: ContainerStartupOptions = {
			image: container.images.api,
			instance: { vcpu: 1, memoryMib: 1024, diskMb: 2000 },
			enableInternet: true,
			env: Object.fromEntries(Object.entries(this.env).filter(([, value]) => typeof value === "string")),
			labels: { version },
		};
		const migrated = await router(this.env).migration(version);
		if (!container.running && migrated === false) {
			throw new Error(`migration failed for version ${version}`);
		}
		if (!container.running && migrated === undefined) {
			this.stopRequested = false;
			container.start({ ...options, entrypoint: MIGRATION_ENTRYPOINT });
			const failure: unknown = await container.monitor().then(
				() => undefined,
				(error: unknown) => error ?? new Error("migration container stopped"),
			);
			if (failure === undefined || !this.stopRequested) {
				await router(this.env).recordMigration(version, failure === undefined);
			}
			if (failure !== undefined) {
				throw failure;
			}
		}
		await container.interceptOutboundHttp(new URL(this.env.QUEUE_URL).hostname, this.ctx.exports.QueuePublisher);
		if (!container.running) {
			container.start(options);
			this.ctx.waitUntil(container.monitor().catch((error) => console.error("api container stopped", error)));
		}
		await container.setInactivityTimeout(INACTIVITY_TIMEOUT_MS);

		const port = container.getTcpPort(PORT);
		let lastError: unknown;
		for (let attempt = 0; attempt < READY_ATTEMPTS && container.running; attempt++) {
			try {
				const response = await port.fetch("http://container/api/healthz", { signal: AbortSignal.timeout(1000) });
				await response.body?.cancel();
				if (response.ok) {
					return;
				}
				lastError = new Error(`healthz returned ${response.status}`);
			} catch (error) {
				lastError = error;
			}
			await scheduler.wait(READY_INTERVAL_MS);
		}
		await this.stop();
		throw new Error("api container did not become ready", { cause: lastError });
	}
}

export class ApiRouter extends DurableObject<Env> {
	static {
		retryable(this.prototype.active);
	}

	private switching: Promise<void> | undefined;

	active(): Color {
		return this.ctx.storage.kv.get<Color>("active") ?? "blue";
	}

	migration(version: string): boolean | undefined {
		return (this.ctx.storage.kv.get<Record<string, boolean>>("migrations") ?? {})[version];
	}

	recordMigration(version: string, succeeded: boolean): void {
		const migrations = this.ctx.storage.kv.get<Record<string, boolean>>("migrations") ?? {};
		this.ctx.storage.kv.put("migrations", { ...migrations, [version]: migrations[version] || succeeded });
	}

	rollout(version: string): void {
		this.switching ??= this.switchIfOutdated(version)
			.catch((error) => console.error("api switch failed", error))
			.finally(() => {
				this.switching = undefined;
			});
		this.ctx.waitUntil(this.switching);
	}

	async runCron(version: string): Promise<void> {
		this.rollout(version);
		await api(this.env, this.active()).runCron();
	}

	private async switchIfOutdated(version: string): Promise<void> {
		const active = this.active();
		if (!(await api(this.env, active).outdated(version))) {
			return;
		}
		const standby = active === "blue" ? "green" : "blue";
		try {
			await api(this.env, standby).prepare(version);
		} catch (error) {
			await api(this.env, standby).stop();
			throw error;
		}
		this.ctx.storage.kv.put("active", standby);
		await scheduler.wait(DRAIN_MS);
		await api(this.env, active).stop();
	}
}

export default {
	async fetch(request, env): Promise<Response> {
		const url = new URL(request.url);
		if (url.protocol === "http:") {
			url.protocol = "https:";
			const permanent = env.ENV !== "prod" || request.method === "GET" || request.method === "HEAD";
			return Response.redirect(url.href, permanent ? 301 : 307);
		}
		let path: string;
		try {
			path = decodeURIComponent(url.pathname);
		} catch {
			return new Response(null, { status: 404 });
		}
		if (path.startsWith("/internal/")) {
			return new Response(null, { status: 404 });
		}

		const forwarded = new Request(request);
		forwarded.headers.delete("CF-IPCountry");
		const country = String(request.cf?.country);
		if (/^[A-Z]{2}$/.test(country) && country !== "XX") {
			forwarded.headers.set("CF-IPCountry", country);
		}
		const stub = api(env, await router(env).active());
		if (path === "/api/healthz") {
			await router(env).rollout(env.VERSION.id);
		}
		let response: Response;
		try {
			response = await stub.fetch(forwarded);
		} catch (error) {
			console.error("api request failed", error);
			response = new Response(null, { status: 502 });
		}
		if (path !== "/api/healthz") {
			return response;
		}
		const headers = new Headers(response.headers);
		headers.set("X-Container-Version", (await stub.version()) || "none");
		return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
	},

	async queue(batch, env): Promise<void> {
		const name = batch.queue.replace(`jn-buddybird-${env.ENV}-`, "");
		for (const message of batch.messages) {
			try {
				const stub = api(env, await router(env).active());
				const response = await stub.fetch(`http://container/internal/queues/${name}`, {
					method: "POST",
					headers: {
						"Content-Type": "application/json",
						"X-Queue-Message-Id": message.id,
						"X-Queue-Attempts": String(message.attempts),
						"X-Queue-Timestamp": String(message.timestamp.getTime()),
					},
					body: JSON.stringify(message.body),
				});
				await response.body?.cancel();
				if (response.ok) {
					message.ack();
				} else {
					message.retry(retryOptions(name, message.attempts));
				}
			} catch (error) {
				console.error("queue message delivery failed", batch.queue, message.id, error);
				message.retry(retryOptions(name, message.attempts));
			}
		}
	},

	async scheduled(_controller, env): Promise<void> {
		await router(env).runCron(env.VERSION.id);
	},
} satisfies ExportedHandler<Env>;
