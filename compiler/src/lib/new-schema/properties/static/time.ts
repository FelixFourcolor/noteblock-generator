import { type } from "arktype";
import { IStatic } from "../meta.js";

export const Time = type("6 <= number.integer <= 48").brand("Time");
export const ITime = IStatic({ time: Time });

export type Time = typeof Time.t;
export type ITime = typeof ITime.t;
