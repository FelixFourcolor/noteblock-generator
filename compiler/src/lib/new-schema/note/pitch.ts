import { type } from "arktype";
import { re } from "#lib/new-schema/regex.js";

const absoluteOctave = re("[1-7]");
const relativeOctave = re.union("_+", "\\^+");

export const octave = Object.assign(re.union(absoluteOctave, relativeOctave), {
	absolute: absoluteOctave,
	relative: relativeOctave,
});

export const Octave = Object.assign(type(octave).brand("Octave"), {
	Absolute: type(absoluteOctave).brand("Octave.Absolute"),
	Relative: type(relativeOctave).brand("Octave.Relative"),
});

const accidental = re.union("#{1,2}", "b{1,2}", "s{0,2}");
const pitchName = re("[a-g]", accidental);

const absolutePitch = re(pitchName, absoluteOctave);
const relativePitch = re(pitchName, relativeOctave);
const impliedPitch = pitchName;

export const pitch = Object.assign(
	re.union(absolutePitch, relativePitch, impliedPitch),
	{
		absolute: absolutePitch,
		relative: relativePitch,
		implied: impliedPitch,
	},
);

export const Pitch = Object.assign(type(pitch).brand("Pitch"), {
	Absolute: type(absolutePitch).brand("Pitch.Absolute"),
	Relative: type(relativePitch).brand("Pitch.Relative"),
	Implied: type(impliedPitch).brand("Pitch.Implied"),
});
