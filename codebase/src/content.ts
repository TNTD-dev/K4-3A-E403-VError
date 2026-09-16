import item from "../content/item.tokenization.v1.json" with { type: "json" };
import sources from "../content/sources.v1.json" with { type: "json" };
import support from "../content/citation-support.v1.json" with { type: "json" };
import { answerKey, ITEM_ID, ITEM_VERSION, SOURCE_VERSION, type MisconceptionId } from "./answer-key.js";

export type ApprovedSource = {
  sourceId: string;
  document: string;
  locator: string;
  excerpt: string;
  conceptIds: string[];
  approvedBy: string;
};

export const publicItem = item;
export const approvedSources = sources as ApprovedSource[];
export const citationSupport = support as Record<MisconceptionId, string[]>;

export function getSource(sourceId: string): ApprovedSource | undefined {
  return approvedSources.find((source) => source.sourceId === sourceId);
}

export function sourceVersionInfo() {
  return { itemId: ITEM_ID, itemVersion: ITEM_VERSION, sourceVersion: SOURCE_VERSION, sources: approvedSources.map((source) => source.sourceId) };
}

export { answerKey, ITEM_ID, ITEM_VERSION, SOURCE_VERSION };
