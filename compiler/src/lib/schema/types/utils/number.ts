import type { tags } from "typia";

export type Int<A extends number = number, B extends number = number> = number &
	tags.Type<"int32"> &
	(number extends A ? unknown : tags.Minimum<A>) &
	(number extends B ? unknown : tags.Maximum<B>);
