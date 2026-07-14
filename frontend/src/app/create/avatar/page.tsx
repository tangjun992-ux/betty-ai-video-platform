import { redirect } from "next/navigation";

/** AI 头像说话能力已合并至唇形同步 — 避免占位页误导用户。 */
export default function AvatarPage() {
  redirect("/create/lipsync");
}
