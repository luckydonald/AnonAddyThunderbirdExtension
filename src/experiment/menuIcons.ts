export const FORMAT_ITEM_VALUES = [
  "random_characters",
  "random_words",
  "random_male_name",
  "random_female_name",
  "random_noun",
  "custom",
] as const;

export type FormatItemValue = (typeof FORMAT_ITEM_VALUES)[number];

export interface MenuIconUrls {
  addy: string;
  existing: string;
  newAlias: string;
  picker: string;
  server: string;
  domain: string;
  alias: string;
  format: Record<FormatItemValue, string>;
}

export function createMenuIconUrls(baseUri: string): MenuIconUrls {
  const base = `${baseUri.replace(/\/?$/, "/")}experiment/icons/`;
  return {
    addy: `${baseUri.replace(/\/?$/, "/")}icon.svg`,
    existing: `${base}existing.svg`,
    newAlias: `${base}new.svg`,
    picker: `${base}picker.svg`,
    server: `${base}server.svg`,
    domain: `${base}domain.svg`,
    alias: `${base}alias.svg`,
    format: {
      random_characters: `${base}format-characters.svg`,
      random_words: `${base}format-words.svg`,
      random_male_name: `${base}format-male-name.svg`,
      random_female_name: `${base}format-female-name.svg`,
      random_noun: `${base}format-noun.svg`,
      custom: `${base}format-custom.svg`,
    },
  };
}
