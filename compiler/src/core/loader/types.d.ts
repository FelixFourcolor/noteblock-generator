import type { FileRef, IProperties, Notes } from "#schema/@";
import type { ValidateError } from "./validate.js";

export type JsonString = `json://${string}`;

export type LoadedVoice = {
	notes: Notes<"lazy">;
	modifier: IProperties;
	name: string | undefined;
};

export type LazyVoice = {
	load: () => Promise<LoadedVoice | ValidateError<{ name: string }>>;
	modifier?: IProperties;
	url?: FileRef;
};

export type LazyVoiceEntry = LazyVoice | LazyVoice[] | null;

export type LoadedSong = {
	voices: LazyVoiceEntry[];
	modifier: IProperties;
};

export type LazySong = () => Promise<{
	song: LoadedSong;
	updates: FileRef[];
}>;
