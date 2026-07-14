import { redirect } from "next/navigation";

/** 内容提取尚未上线 — 引导至 Agent 工作流，避免「即将推出」死胡同。 */
export default function ExtractPage() {
  redirect("/agent");
}
