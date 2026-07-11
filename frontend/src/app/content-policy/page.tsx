import { LegalDoc } from "@/components/LegalDoc";

export const metadata = { title: "内容政策" };

export default function ContentPolicyPage() {
  return (
    <LegalDoc
      title="内容政策"
      updated="2026 年 7 月 11 日"
      intro="为营造安全、合规、可信的创作环境，所有在 betty 上生成、上传与分享的内容都须遵守本内容政策。我们通过生成前提示词预审、生成后审核与用户举报共同维护社区。"
      sections={[
        { h: "禁止的内容", body: <ul className="list-disc pl-5 space-y-1">
          <li>色情、露骨性内容，以及任何涉及未成年人的不当内容。</li>
          <li>真实人物的深度伪造（未经同意的换脸/拟声）、误导性冒充。</li>
          <li>暴力血腥、恐怖主义、自残、仇恨与歧视性内容。</li>
          <li>侵犯他人知识产权、商标、肖像权或隐私的内容。</li>
          <li>欺诈、虚假信息、恶意软件或其他违法用途。</li>
        </ul> },
        { h: "受限内容", body: <p>涉及公众人物、品牌标识、政治敏感或医疗/金融建议等内容需谨慎使用，并遵守相关法律法规；我们可能对其施加额外限制或标注。</p> },
        { h: "审核机制", body: <p>提交生成时，系统会对提示词进行<strong>预审拦截</strong>；生成结果进入公开展示前会经过审核；同时开放<strong>一键举报</strong>。命中违规的内容将被拦截或下架，账户视情节接受警告至封禁。</p> },
        { h: "举报与申诉", body: <p>您可对任意公开作品发起举报，我们会尽快复核并处理。若您认为处置有误，可通过 abuse@betty.ai 提交申诉。</p> },
        { h: "创作者责任", body: <p>您对使用本平台创作与发布的内容承担最终责任，须确保拥有必要授权并遵守所在地法律。</p> },
      ]}
    />
  );
}
