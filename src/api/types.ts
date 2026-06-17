export type AliasFormat =
  | "random_characters"
  | "random_words"
  | "random_male_name"
  | "random_female_name"
  | "random_noun"
  | "custom";

export interface DomainOptions {
  data: string[];
  defaultAliasDomain: string;
  defaultAliasFormat: AliasFormat;
}

export interface Alias {
  id: string;
  local_part: string;
  domain: string;
  email: string;
  active: boolean;
  description: string | null;
}

export interface PaginatedAliases {
  data: Alias[];
  meta: {
    current_page: number;
    last_page: number;
  };
}

export interface CreateAliasBody {
  domain: string;
  description: string;
  format?: AliasFormat;
  local_part?: string;
}
