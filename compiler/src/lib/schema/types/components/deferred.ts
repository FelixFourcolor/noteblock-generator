export type FileRef = `file://${string}`;

export type JsonData = `json://${string}`;

export type Deferred<
	Data extends object,
	Options extends { allowJson: boolean } = { allowJson: false },
> = Data | FileRef | (Options["allowJson"] extends true ? JsonData : never);
