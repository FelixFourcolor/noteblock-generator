import { type Type, type } from "arktype";

export const FileRef = type(/^file:\/\/.+/).brand("FileRef");
export const JsonData = type(/^json:\/\/.+/).brand("JsonData");

export function Deferred<Data extends object>(
	data: Type<Data>,
): Type<Deferred<Data>> {
	return type.or(
		data as any, //
		FileRef,
		JsonData,
	) as unknown as Type<Deferred<Data>>;
}

export type FileRef = typeof FileRef.t;
export type JsonData = typeof JsonData.t;

export type Deferred<Data extends object> = Data | FileRef | JsonData;
