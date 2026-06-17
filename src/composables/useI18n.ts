export function useI18n() {
  function t(key: string, ...substitutions: string[]): string {
    return messenger.i18n.getMessage(
      key,
      substitutions.length ? substitutions : undefined,
    );
  }
  return { t };
}
