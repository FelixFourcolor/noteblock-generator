import { type } from "arktype";
import { IStatic } from "../meta.js";

export const Beat = type("1 <= number.integer <= 12").brand("Beat");
export const IBeat = IStatic({ beat: Beat });

export type Beat = typeof Beat.t;
export type IBeat = typeof IBeat.t;
