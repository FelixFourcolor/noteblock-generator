import type { tags } from "typia";

type TDoc = { title?: string; description?: string };

export type WithDoc<Target, Doc extends TDoc | undefined> = Doc extends TDoc
	? Target & tags.JsonSchemaPlugin<Doc>
	: Target;

export type ExtractDoc<
	T,
	__doc extends TDoc | unknown = ExtractDocHelper<T>,
> = __doc extends TDoc ? __doc : undefined;

type ExtractDocHelper<T> = (T extends tags.JsonSchemaPlugin<{ title: infer U }>
	? { title: U }
	: unknown) &
	(T extends tags.JsonSchemaPlugin<{ description: infer V }>
		? { description: V }
		: unknown);
