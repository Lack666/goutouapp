import type { components, paths, UUID } from '../src/api/generated/client';
import { createApiClient } from '../src/api/generated/client';
// Compile-only assertions. No manually maintained wire DTOs and no API call.
export function contractChecks(id: UUID, client: ReturnType<typeof createApiClient>) {
  const valid: components['schemas']['ConversationCreateRequest'] = { id };
  const nullable: components['schemas']['ConversationResponse'] = {
    id,
    relationship_id: null,
    created_at: '',
    updated_at: '',
  };
  // @ts-expect-error required ID
  const missing: components['schemas']['PersonCreateRequest'] = { display_name: 'synthetic' };
  const demo: components['schemas']['PersonCreateRequest'] = {
    // @ts-expect-error synthetic IDs cannot satisfy generated UUID
    id: 'demo-a',
    display_name: 'synthetic',
  };
  // @ts-expect-error response requires nullable field to be present
  const omitted: components['schemas']['ConversationResponse'] = {
    id,
    created_at: '',
    updated_at: '',
  };
  // @ts-expect-error Person name cannot be null
  const nullName: components['schemas']['PersonCreateRequest'] = { id, display_name: null };
  const error: paths['/api/v1/persons']['get']['responses'][401]['content']['application/json'] = {
    error: { code: 'invalid_credential', message: 'safe' },
  };
  // @ts-expect-error closed operation paths
  void client.GET('/invented');
  return [valid, nullable, missing, demo, omitted, nullName, error];
}
