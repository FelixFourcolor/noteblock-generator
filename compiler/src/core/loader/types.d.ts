import type {
	FileRef,
	SequentialNotes,
	SongModifier,
	VoiceModifier,
} from "@/types/schema";
import type { ValidateError } from "./validate";

export type JsonString = `json://${string}`;

export type LoadedVoice = {
	notes: SequentialNotes<"lazy">;
	modifier: VoiceModifier;
	name: string | undefined;
};

export type LazyVoice = {
	load: () => Promise<LoadedVoice | ValidateError<{ name: string }>>;
	modifier?: VoiceModifier;
	url?: FileRef;
};

export type LazyVoiceEntry = LazyVoice | LazyVoice[] | null;

export type LoadedSong = {
	voices: LazyVoiceEntry[];
	modifier: SongModifier;
};

export type LazySong = () => Promise<{
	song: LoadedSong;
	updates: FileRef[];
}>;
