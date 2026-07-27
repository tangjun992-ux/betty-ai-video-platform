import { redirect } from "next/navigation";

/** `/create` 入口：跳转到 Tools Hub，避免裸路径 404。 */
export default function CreateIndexPage() {
  redirect("/tools");
}
