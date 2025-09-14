import { type } from "arktype";
import { re } from "#lib/new-schema/regex.js";

const allowedChars = "[\\w\\s]";
const length = "{4,}";

export const name = re(allowedChars, length);
export const Name = type(name).brand("Name");
export const IName = type({ "name?": Name });

export type Name = typeof Name.t;
export type IName = typeof IName.t;
