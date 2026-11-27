#!/bin/sh
set -eu

environment=${1:-}
action=${2:-resources}

case "$environment:$action" in
	dev:resources | prod:resources | local:resources | dev:notifications | prod:notifications | local:notifications) ;;
	*)
		echo "usage: npm run provision -- <dev|prod|local> [resources|notifications]" >&2
		exit 1
		;;
esac

cd "$(dirname "$0")"

export CLOUDFLARE_ACCOUNT_ID=0c4453da6d81adec04df8132e00660c4

bucket=jn-buddybird-data-$environment
queue_prefix=jn-buddybird-$environment

if [ "$action" = notifications ]; then
	for prefix in upload/ user/; do
		wrangler r2 bucket notification create "$bucket" \
			--event-types object-create --prefix "$prefix" --queue "$queue_prefix-upload-confirmation"
	done

	exit
fi

wrangler r2 bucket info "$bucket" > /dev/null 2>&1 || wrangler r2 bucket create "$bucket" --location apac --no-update-config
wrangler r2 bucket lifecycle set "$bucket" --file lifecycle.json --force
wrangler r2 bucket cors set "$bucket" --file "cors.$environment.json" --force

for name in upload-confirmation parrot-sound-detection mimicry-judgment judgment-result notification withdrawal; do
	for queue in "$queue_prefix-$name" "$queue_prefix-$name-dlq"; do
		wrangler queues info "$queue" > /dev/null 2>&1 || wrangler queues create "$queue"
	done

	wrangler queues update "$queue_prefix-$name-dlq" --message-retention-period-secs 1209600
done

if [ "$environment" = local ]; then
	for name in upload-confirmation judgment-result notification withdrawal parrot-sound-detection-dlq mimicry-judgment-dlq; do
		wrangler queues consumer http list "$queue_prefix-$name" --json | grep -q http_pull \
			|| wrangler queues consumer http add "$queue_prefix-$name"
	done
fi
