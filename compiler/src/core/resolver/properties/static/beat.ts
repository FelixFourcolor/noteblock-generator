import type { Beat as T_Beat } from "@/types/schema";
import { Static } from "../static";

export const Beat = Static<T_Beat>({ Default: 4 });
