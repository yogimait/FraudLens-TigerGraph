import { Controller, Get, Post, Body, Param } from '@nestjs/common';
import { CasesService } from './cases.service.js';

@Controller('cases')
export class CasesController {
  constructor(private readonly casesService: CasesService) {}

  @Get('stats')
  async getStats() {
    return this.casesService.getStats();
  }

  @Get()
  async findAll() {
    return this.casesService.findAll();
  }

  @Get(':id')
  async findOne(@Param('id') id: string) {
    return this.casesService.findOne(id);
  }

  @Post(':id/trigger')
  async trigger(
    @Param('id') id: string, 
    @Body('transaction_id') transaction_id: string,
    @Body('trigger_type') trigger_type: string
  ) {
    return this.casesService.triggerInvestigation(id, transaction_id, trigger_type);
  }

  @Post(':id/approve')
  async approve(
    @Param('id') id: string,
    @Body('level') level: string,
    @Body('reason') reason: string
  ) {
    return this.casesService.approveCase(id, 'approved', level, reason);
  }

  @Post(':id/reject')
  async reject(
    @Param('id') id: string,
    @Body('level') level: string,
    @Body('reason') reason: string
  ) {
    return this.casesService.approveCase(id, 'rejected', level, reason);
  }
}
