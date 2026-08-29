import { AlertTriangle } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { Persona, PersonaDisagreement } from "@/types";

function averageScore(scores: PersonaDisagreement["variant_a_scores"]): number {
  return (
    (scores.average_clarity_score +
      scores.average_perceived_value_score +
      scores.average_adoption_intent_score) /
    3
  );
}

export function PersonaDisagreementCard({
  disagreement,
  personas,
}: {
  disagreement: PersonaDisagreement[];
  personas: Persona[];
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Persona disagreement</CardTitle>
      </CardHeader>
      <CardContent>
        {disagreement.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No persona-level disagreement detected between variants.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Persona</TableHead>
                  <TableHead>Variant A avg</TableHead>
                  <TableHead>Variant B avg</TableHead>
                  <TableHead>Direction</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {disagreement.map((item) => (
                  <TableRow key={item.persona_id}>
                    <TableCell>
                      {personas.find((p) => p.id === item.persona_id)?.name ??
                        `Persona #${item.persona_id}`}
                    </TableCell>
                    <TableCell>{averageScore(item.variant_a_scores).toFixed(1)}</TableCell>
                    <TableCell>{averageScore(item.variant_b_scores).toFixed(1)}</TableCell>
                    <TableCell>
                      <span className="inline-flex items-center gap-1">
                        {item.direction}
                        {item.diverges_from_overall_variant_direction ? (
                          <AlertTriangle
                            className="size-3.5 text-amber-600"
                            aria-label="Diverges from overall variant direction"
                          />
                        ) : null}
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
