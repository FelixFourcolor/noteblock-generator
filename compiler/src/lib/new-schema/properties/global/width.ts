import { type } from "arktype";

export const Width = type("8 <= number.integer <= 16").brand("Width");
export const IWidth = type({ "width?": Width });

export type Width = typeof Width.t;
export type IWidth = typeof IWidth.t;
