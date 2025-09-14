import { type } from "arktype";
import { IStatic } from "../meta.js";

export const Delay = type("1 <= number.integer <= 4").brand("Delay");
export const IDelay = IStatic({ delay: Delay });

export type Delay = typeof Delay.t;
export type IDelay = typeof IDelay.t;
