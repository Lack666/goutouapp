import { useLocalSearchParams, useRouter } from 'expo-router';

export function useRelationshipScope(): string | null {
  const { relationshipId } = useLocalSearchParams<{ relationshipId?: string | string[] }>();
  // Ambiguous repeated query parameters fail closed rather than selecting another scope.
  return Array.isArray(relationshipId) ? '__unavailable__' : (relationshipId ?? null);
}
export function useLocalNavigation() {
  const router = useRouter();
  return {
    back: () => (router.canGoBack() ? router.back() : router.replace('/')),
    open: (
      pathname: '/chat' | '/import' | '/history' | '/relationship',
      relationshipId: string | null,
    ) => router.push({ pathname, params: relationshipId === null ? {} : { relationshipId } }),
    select: (relationshipId: string) => router.setParams({ relationshipId }),
  };
}
