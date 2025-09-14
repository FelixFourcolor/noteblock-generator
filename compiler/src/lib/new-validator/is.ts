import { type Type, type } from "arktype";

export function is<T>(Type: Type<T>, value: unknown): value is T {
	return !(Type(value) instanceof type.errors);
}
