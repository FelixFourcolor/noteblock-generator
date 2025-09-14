import { type } from "arktype";
import { re } from "../regex.js";

const line = `\\|{1,2}`; // a bar line, optionally 2 lines to rest the entire bar
const unsafeFlag = `\\!`; // ignore any barline errors
const barNumber = `\\d+`;

export const barLine = re(barNumber, "?", line, unsafeFlag, "?");
export const BarLine = type(barLine).brand("BarLine");

export type BarLine = typeof BarLine.t;
