import type { Re } from "#core/types/utils/@";

export type Name = Re<"[\\w\\s]", "{4,}">;
export interface IName {
	name: Name;
}
