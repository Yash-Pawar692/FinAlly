import { execSync } from "node:child_process";

/**
 * Restarts the sibling `app` service container via the host Docker socket
 * (mounted into the playwright container — see test/Dockerfile and
 * docker-compose.test.yml). Used by the SSE resilience scenario (PLAN.md §12)
 * to force a real disconnect/reconnect of the EventSource connection.
 */
// Matches the fixed `name:` in docker-compose.test.yml, scoping the lookup to
// this stack so it can't accidentally restart an unrelated "app" container.
const COMPOSE_PROJECT = "finally-e2e";

export function restartAppContainer(): void {
  const id = execSync(
    `docker ps --filter "label=com.docker.compose.project=${COMPOSE_PROJECT}" ` +
      '--filter "label=com.docker.compose.service=app" --format "{{.ID}}"'
  )
    .toString()
    .trim()
    .split("\n")[0];

  if (!id) {
    throw new Error(`Could not find the running app container for compose project "${COMPOSE_PROJECT}"`);
  }

  execSync(`docker restart ${id}`);
}
