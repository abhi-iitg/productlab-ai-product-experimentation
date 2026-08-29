import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ResponsibleAiNotice } from "@/components/layout/responsible-ai-notice";
import { RecommendationBadge } from "@/components/decision-memo/recommendation-badge";
import { formatDate } from "@/lib/formatting";
import type { DecisionMemo } from "@/types";

function ListCard({ title, items }: { title: string; items: string[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="list-inside list-disc space-y-1 text-sm text-foreground">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

export function DecisionMemoView({ memo }: { memo: DecisionMemo }) {
  return (
    <div className="space-y-4">
      <ResponsibleAiNotice />

      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <RecommendationBadge recommendation={memo.recommendation} />
            <span className="text-xs text-muted-foreground">
              Generated {formatDate(memo.created_at)}
            </span>
          </div>
          <CardTitle className="text-base">Executive summary</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-foreground">{memo.executive_summary}</p>
        </CardContent>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2">
        <ListCard title="Supporting findings" items={memo.supporting_findings} />
        <ListCard title="Weakest assumptions" items={memo.weakest_assumptions} />
        <ListCard title="Recommended product changes" items={memo.recommended_product_changes} />
        <ListCard title="Risks" items={memo.risks} />
        <ListCard title="Recommended success metrics" items={memo.recommended_success_metrics} />
        {memo.uncertain_conclusions.length > 0 ? (
          <ListCard title="Uncertain conclusions" items={memo.uncertain_conclusions} />
        ) : null}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recommended real-user test plan</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div>
            <p className="text-xs font-medium text-muted-foreground">Objective</p>
            <p className="text-foreground">{memo.real_user_test.objective}</p>
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground">Target participants</p>
            <ul className="list-inside list-disc text-foreground">
              {memo.real_user_test.target_participants.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground">Method</p>
            <p className="text-foreground">{memo.real_user_test.method}</p>
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground">Sample-size rationale</p>
            <p className="text-foreground">{memo.real_user_test.sample_size_rationale}</p>
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground">Tasks or questions</p>
            <ul className="list-inside list-disc text-foreground">
              {memo.real_user_test.tasks_or_questions.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground">Success metrics</p>
            <ul className="list-inside list-disc text-foreground">
              {memo.real_user_test.success_metrics.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground">Stopping rule</p>
            <p className="text-foreground">{memo.real_user_test.stopping_rule}</p>
          </div>
        </CardContent>
      </Card>

      <p className="text-xs text-muted-foreground">
        Supporting insights: {memo.supporting_insight_ids.map((id) => `#${id}`).join(", ")}
        {" · "}Prompt version {memo.prompt_version} · Model {memo.model_name}
      </p>
    </div>
  );
}
