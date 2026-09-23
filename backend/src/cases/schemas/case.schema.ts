import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { Document } from 'mongoose';

export type CaseDocument = InvestigationCase & Document;

export class EvidenceItem {
  claim: string;
  source: string; // graph | document | customer | external
  ref: string;
  entity_ids: string[];
}

export class EvidenceRequest {
  type: string;
  asked_after_step: number;
  assumed_response: string;
}

@Schema({ timestamps: true })
export class InvestigationCase {
  @Prop({ required: true, unique: true })
  case_id: string;

  @Prop({ required: true })
  transaction_id: string;

  @Prop({ default: 'pending' })
  status: string; // pending, investigating, awaiting_approval, closed, failed

  @Prop()
  trigger_type: string;

  @Prop()
  fraud_probability: number;

  @Prop()
  pattern: string;

  @Prop()
  pattern_description: string;

  @Prop()
  verdict: string;

  @Prop()
  exposure_usd: number;

  @Prop([String])
  affected_txn_ids: string[];

  @Prop()
  first_suspicious_txn_id: string;

  @Prop([String])
  connected_card_ids: string[];

  @Prop([String])
  connected_device_profiles: string[];

  @Prop({ type: Object })
  evidence: EvidenceItem[];

  @Prop({ type: Object })
  evidence_requests: EvidenceRequest[];

  @Prop([String])
  similar_prior_cases: string[];

  @Prop({ default: false })
  written_to_graph: boolean;

  @Prop()
  graph_case_id: string;

  @Prop({ type: Object })
  sar: {
    file: boolean;
    reason: string;
    narrative: string;
    subjects: string[];
    total_amount_usd: number;
    activity_dates: string[];
  };

  @Prop({ type: Object })
  next_best_actions: {
    initial: any[];
    final: any[];
    what_changed: string;
  };

  @Prop()
  stop_reason: string;

  @Prop()
  summary: string;

  @Prop()
  tool_calls: number;

  @Prop()
  tokens: number;

  @Prop()
  latency_s: number;

  @Prop({ type: Object })
  graph_data: {
    nodes: any[];
    edges: any[];
  };

  @Prop({ type: Object })
  analyst_notes: {
    analyst: string;
    note: string;
    timestamp: Date;
  }[];

  @Prop({ type: Object })
  approval_status: {
    decision: string;
    level: string;
    reason: string;
    timestamp: Date;
  };

  @Prop({ type: Object })
  metadata: {
    duration_seconds: number;
    stop_reason: string;
    jev_classification: any;
    evidence_count: number;
  };
}

export const CaseSchema = SchemaFactory.createForClass(InvestigationCase);
