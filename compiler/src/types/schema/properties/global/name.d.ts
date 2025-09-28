import type { Re } from "#types/utils/@";

export type Name = Re<"[\\w\\s]", "{4,}">;

export type IName = { name?: Name };
