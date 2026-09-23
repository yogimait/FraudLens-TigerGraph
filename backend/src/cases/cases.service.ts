import { Injectable, Logger, NotFoundException, BadRequestException, ConflictException } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { InvestigationCase, CaseDocument } from './schemas/case.schema.js';
import axios from 'axios';

const L2_ACTIONS = ['FILE_REPORT', 'BLOCK_ALL_CARDS'];

@Injectable()
export class CasesService {
  private readonly logger = new Logger(CasesService.name);
  private readonly agentUrl = process.env.AGENT_URL || 'http://localhost:8000';

  constructor(
    @InjectModel(InvestigationCase.name) private caseModel: Model<CaseDocument>,
  ) {}

  async findAll(): Promise<CaseDocument[]> {
    return this.caseModel.find().sort({ createdAt: -1 }).exec();
  }

  async findOne(case_id: string): Promise<CaseDocument> {
    const caseData = await this.caseModel.findOne({ case_id }).exec();
    if (!caseData) {
      throw new NotFoundException(`Case ${case_id} not found`);
    }
    return caseData;
  }

  requiredApprovalLevel(c: InvestigationCase): 'L1' | 'L2' | null {
    const actions: any[] = c.next_best_actions?.final || [];
    if (!actions.length) return null;
    const names = actions.map((a) => a.action);
    const exposure = c.exposure_usd || 0;
    const isL2 =
      names.some((n) => L2_ACTIONS.includes(n)) ||
      (names.includes('BLOCK_CARD') && exposure > 2500);
    if (isL2) return 'L2';
    if (actions.some((a) => a.route === 'L1')) return 'L1';
    return null;
  }

  async getStats() {
    const cases = await this.caseModel.find().exec();
    const total = cases.length;
    const awaiting_approval = cases.filter(c => c.status === 'awaiting_approval').length;
    const investigating = cases.filter(c => c.status === 'investigating').length;
    const closed = cases.filter(c => c.status === 'closed').length;
    const closed_fraud = cases.filter(c => c.status === 'closed' && c.verdict === 'fraud').length;
    const closed_legitimate = cases.filter(c => c.status === 'closed' && c.verdict === 'legitimate').length;
    const uncertain = cases.filter(c => c.verdict === 'uncertain').length;
    const sars_generated = cases.filter(c => c.sar?.file === true).length;
    const escalated = cases.filter(c => this.requiredApprovalLevel(c) !== null).length;

    return {
      total,
      open: investigating,
      awaiting_approval,
      closed,
      closed_fraud,
      closed_legitimate,
      uncertain,
      sars_generated,
      escalated
    };
  }

  async triggerInvestigation(case_id: string, transaction_id: string, trigger_type: string = 'risk_score') {
    let caseData = await this.caseModel.findOne({ case_id }).exec();
    if (!caseData) {
      caseData = new this.caseModel({
        case_id,
        transaction_id,
        trigger_type,
        status: 'investigating'
      });
    } else {
      caseData.status = 'investigating';
    }
    await caseData.save();

    try {
      const response = await axios.post(`${this.agentUrl}/investigate`, {
        case_id,
        transaction_id,
        trigger_type
      }, { timeout: 120000 }); // 2 minute timeout

      const result = response.data;
      const agentCase = result.case || {};

      caseData.status = 'awaiting_approval';
      caseData.fraud_probability = agentCase.fraud_probability;
      caseData.pattern = agentCase.pattern;
      caseData.pattern_description = agentCase.pattern_description;
      caseData.verdict = agentCase.verdict;
      caseData.exposure_usd = agentCase.exposure_usd;
      caseData.affected_txn_ids = agentCase.affected_txn_ids;
      caseData.first_suspicious_txn_id = agentCase.first_suspicious_txn_id;
      caseData.connected_card_ids = agentCase.connected_card_ids;
      caseData.connected_device_profiles = agentCase.connected_device_profiles;
      caseData.similar_prior_cases = agentCase.similar_prior_cases;
      caseData.written_to_graph = agentCase.written_to_graph;
      caseData.graph_case_id = agentCase.graph_case_id;
      caseData.evidence = agentCase.evidence;
      caseData.sar = result.sar;
      caseData.evidence_requests = result.evidence_requests;
      caseData.next_best_actions = result.next_best_actions;
      caseData.stop_reason = result.stop_reason ?? result.metadata?.stop_reason;
      caseData.summary = agentCase.summary || '';
      caseData.tool_calls = result.tool_calls;
      caseData.tokens = result.tokens;
      caseData.latency_s = result.latency_s;
      caseData.graph_data = result.graph_data;
      caseData.metadata = result.metadata;

      if (this.requiredApprovalLevel(caseData) === null) {
        caseData.status = 'closed';
      }

      await caseData.save();
      return caseData;
    } catch (error: any) {
      this.logger.error(`Failed to trigger agent for case ${case_id}:`, error.message);
      caseData.status = 'failed';
      await caseData.save();
      throw new BadRequestException(`Agent investigation failed: ${error.message}`);
    }
  }

  async approveCase(case_id: string, decision: 'approved' | 'rejected', level: string, reason: string) {
    if (level !== 'L1' && level !== 'L2') {
      throw new BadRequestException('level must be "L1" or "L2"');
    }
    const caseData = await this.findOne(case_id);

    const required = this.requiredApprovalLevel(caseData);
    if (required) {
      const rank: Record<string, number> = { L1: 1, L2: 2 };
      if (rank[level] < rank[required]) {
        throw new ConflictException(
          `Case requires ${required} approval; ${level} cannot approve it`
        );
      }
    }

    caseData.approval_status = {
      decision,
      level,
      reason,
      timestamp: new Date()
    };

    caseData.status = 'closed';

    await caseData.save();
    return caseData;
  }
}
