export type ResearchPhase =
  | 'architecting'
  | 'awaiting_outline_approval'
  | 'planning'
  | 'researching'
  | 'analyzing'
  | 'writing'
  | 'reviewing'
  | 'completed'

export type OutlineSectionType = 'qualitative' | 'quantitative' | 'mixed'

export interface OutlineSection {
  id: string
  title: string
  description: string
  section_type: OutlineSectionType
  requires_data: boolean
  requires_chart: boolean
}

export interface ResearchQuestion {
  id: string
  text: string
}

export interface EditableResearchPlan {
  sections: OutlineSection[]
  researchQuestions: ResearchQuestion[]
}

export interface OutlinePendingApprovalEvent {
  type: 'outline_pending_approval'
  session_id: string
  outline_revision: string
  sections: OutlineSection[]
  research_questions: ResearchQuestion[]
}

export interface PlanningErrorEvent {
  type: 'planning_error'
  content?: string
  error?: string
}

export interface PhaseEvent {
  type: 'phase'
  phase?: string
  content?: string
}

export interface GenericResearchEvent {
  type: string
  [key: string]: unknown
}

export type ResearchEvent =
  | OutlinePendingApprovalEvent
  | PlanningErrorEvent
  | PhaseEvent
  | GenericResearchEvent
