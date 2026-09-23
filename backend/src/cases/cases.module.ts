import { Module } from '@nestjs/common';
import { MongooseModule } from '@nestjs/mongoose';
import { CasesController } from './cases.controller.js';
import { CasesService } from './cases.service.js';
import { InvestigationCase, CaseSchema } from './schemas/case.schema.js';

@Module({
  imports: [
    MongooseModule.forFeature([{ name: InvestigationCase.name, schema: CaseSchema }]),
  ],
  controllers: [CasesController],
  providers: [CasesService],
})
export class CasesModule {}
