import {
  Alert,
  Button,
  Card,
  Checkbox,
  Input,
  Select,
  Space,
  Typography,
} from 'antd'
import { useEffect, useRef, useState } from 'react'

import {
  clearOutlineDraft,
  loadOutlineDraft,
  saveOutlineDraft,
} from './outline-draft'
import type {
  EditableResearchPlan,
  OutlineSection,
  OutlineSectionType,
  ResearchQuestion,
} from './types'

const { Paragraph, Text, Title } = Typography

export interface OutlineApprovalPanelProps {
  sessionId: string
  outlineRevision: string
  initialSections: OutlineSection[]
  initialResearchQuestions: ResearchQuestion[]
  approving: boolean
  error?: string
  onApprove(plan: EditableResearchPlan): Promise<void>
}

function createId(prefix: string): string {
  const id = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`
  return `${prefix}-${id}`
}

function clonePlan(
  sections: OutlineSection[],
  researchQuestions: ResearchQuestion[],
): EditableResearchPlan {
  return {
    sections: sections.map((section) => ({ ...section })),
    researchQuestions: researchQuestions.map((question) => ({ ...question })),
  }
}

function moveItem<T>(items: T[], from: number, to: number): T[] {
  if (to < 0 || to >= items.length) return items
  const result = [...items]
  const [item] = result.splice(from, 1)
  result.splice(to, 0, item)
  return result
}

function planIsValid(plan: EditableResearchPlan): boolean {
  const sectionsValid =
    plan.sections.length >= 3 &&
    plan.sections.length <= 12 &&
    plan.sections.every(
      (section) => section.title.trim() && section.description.trim(),
    )
  const questionsValid =
    plan.researchQuestions.length >= 3 &&
    plan.researchQuestions.length <= 12 &&
    plan.researchQuestions.every((question) => question.text.trim())
  return Boolean(sectionsValid && questionsValid)
}

export function OutlineApprovalPanel({
  sessionId,
  outlineRevision,
  initialSections,
  initialResearchQuestions,
  approving,
  error,
  onApprove,
}: OutlineApprovalPanelProps) {
  const [plan, setPlan] = useState<EditableResearchPlan>(() => {
    const draft = loadOutlineDraft(sessionId, outlineRevision)
    return draft ?? clonePlan(initialSections, initialResearchQuestions)
  })
  const [submitting, setSubmitting] = useState(false)
  const approvedRef = useRef(false)
  const disabled = approving || submitting
  const valid = planIsValid(plan)

  useEffect(() => {
    approvedRef.current = false
  }, [sessionId, outlineRevision])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (!approvedRef.current) {
        saveOutlineDraft(sessionId, outlineRevision, plan)
      }
    }, 800)
    return () => window.clearTimeout(timer)
  }, [outlineRevision, plan, sessionId])

  const updateSection = (index: number, patch: Partial<OutlineSection>) => {
    setPlan((current) => ({
      ...current,
      sections: current.sections.map((section, sectionIndex) =>
        sectionIndex === index ? { ...section, ...patch } : section,
      ),
    }))
  }

  const updateQuestion = (index: number, text: string) => {
    setPlan((current) => ({
      ...current,
      researchQuestions: current.researchQuestions.map((question, questionIndex) =>
        questionIndex === index ? { ...question, text } : question,
      ),
    }))
  }

  const addSection = () => {
    if (plan.sections.length >= 12) return
    setPlan((current) => ({
      ...current,
      sections: [
        ...current.sections,
        {
          id: createId('section'),
          title: '',
          description: '',
          section_type: 'mixed',
          requires_data: false,
          requires_chart: false,
        },
      ],
    }))
  }

  const addQuestion = () => {
    if (plan.researchQuestions.length >= 12) return
    setPlan((current) => ({
      ...current,
      researchQuestions: [
        ...current.researchQuestions,
        { id: createId('question'), text: '' },
      ],
    }))
  }

  const approve = async () => {
    if (!valid || disabled) return
    setSubmitting(true)
    try {
      await onApprove(plan)
      approvedRef.current = true
      clearOutlineDraft(sessionId, outlineRevision)
    } catch {
      // The parent renders the API error and the local draft is preserved.
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card style={{ marginTop: 16 }}>
      <Title level={4}>Review the research outline</Title>
      <Paragraph>
        Edit the chapters and research questions before deep research begins.
        The report will contain at least three chapters.
      </Paragraph>

      {error ? <Alert type="error" showIcon message={error} /> : null}

      <Title level={5} style={{ marginTop: 20 }}>
        Chapters ({plan.sections.length}/12)
      </Title>
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        {plan.sections.map((section, index) => (
          <Card key={section.id} size="small" title={`Chapter ${index + 1}`}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Input
                aria-label={`Chapter ${index + 1} title`}
                disabled={disabled}
                value={section.title}
                placeholder="Chapter title"
                onChange={(event) =>
                  updateSection(index, { title: event.target.value })
                }
              />
              <Input.TextArea
                aria-label={`Chapter ${index + 1} description`}
                disabled={disabled}
                value={section.description}
                placeholder="What this chapter should investigate"
                autoSize={{ minRows: 2, maxRows: 5 }}
                onChange={(event) =>
                  updateSection(index, { description: event.target.value })
                }
              />
              <Space wrap>
                <Select<OutlineSectionType>
                  aria-label={`Chapter ${index + 1} type`}
                  disabled={disabled}
                  value={section.section_type}
                  options={[
                    { value: 'qualitative', label: 'Qualitative' },
                    { value: 'quantitative', label: 'Quantitative' },
                    { value: 'mixed', label: 'Mixed' },
                  ]}
                  onChange={(section_type) =>
                    updateSection(index, { section_type })
                  }
                />
                <Checkbox
                  disabled={disabled}
                  checked={section.requires_data}
                  onChange={(event) =>
                    updateSection(index, { requires_data: event.target.checked })
                  }
                >
                  Requires data
                </Checkbox>
                <Checkbox
                  disabled={disabled}
                  checked={section.requires_chart}
                  onChange={(event) =>
                    updateSection(index, { requires_chart: event.target.checked })
                  }
                >
                  Requires chart
                </Checkbox>
              </Space>
              <Space wrap>
                <Button
                  aria-label={`Move chapter ${index + 1} up`}
                  disabled={disabled || index === 0}
                  onClick={() =>
                    setPlan((current) => ({
                      ...current,
                      sections: moveItem(current.sections, index, index - 1),
                    }))
                  }
                >
                  Up
                </Button>
                <Button
                  aria-label={`Move chapter ${index + 1} down`}
                  disabled={disabled || index === plan.sections.length - 1}
                  onClick={() =>
                    setPlan((current) => ({
                      ...current,
                      sections: moveItem(current.sections, index, index + 1),
                    }))
                  }
                >
                  Down
                </Button>
                <Button
                  danger
                  aria-label={`Delete chapter ${index + 1}`}
                  disabled={disabled || plan.sections.length <= 3}
                  onClick={() =>
                    setPlan((current) => ({
                      ...current,
                      sections: current.sections.filter(
                        (_, sectionIndex) => sectionIndex !== index,
                      ),
                    }))
                  }
                >
                  Delete
                </Button>
              </Space>
            </Space>
          </Card>
        ))}
      </Space>
      <Button
        aria-label="Add chapter"
        style={{ marginTop: 12 }}
        disabled={disabled || plan.sections.length >= 12}
        onClick={addSection}
      >
        Add chapter
      </Button>
      {plan.sections.some(
        (section) => !section.title.trim() || !section.description.trim(),
      ) ? (
        <Text type="danger" style={{ display: 'block', marginTop: 8 }}>
          Chapter titles and descriptions cannot be blank
        </Text>
      ) : null}

      <Title level={5} style={{ marginTop: 24 }}>
        Research questions ({plan.researchQuestions.length}/12)
      </Title>
      <Space direction="vertical" style={{ width: '100%' }}>
        {plan.researchQuestions.map((question, index) => (
          <Space key={question.id} style={{ width: '100%' }} align="start">
            <Input.TextArea
              aria-label={`Research question ${index + 1}`}
              disabled={disabled}
              value={question.text}
              autoSize={{ minRows: 1, maxRows: 4 }}
              onChange={(event) => updateQuestion(index, event.target.value)}
            />
            <Button
              aria-label={`Move question ${index + 1} up`}
              disabled={disabled || index === 0}
              onClick={() =>
                setPlan((current) => ({
                  ...current,
                  researchQuestions: moveItem(
                    current.researchQuestions,
                    index,
                    index - 1,
                  ),
                }))
              }
            >
              Up
            </Button>
            <Button
              aria-label={`Move question ${index + 1} down`}
              disabled={disabled || index === plan.researchQuestions.length - 1}
              onClick={() =>
                setPlan((current) => ({
                  ...current,
                  researchQuestions: moveItem(
                    current.researchQuestions,
                    index,
                    index + 1,
                  ),
                }))
              }
            >
              Down
            </Button>
            <Button
              danger
              aria-label={`Delete question ${index + 1}`}
              disabled={disabled || plan.researchQuestions.length <= 3}
              onClick={() =>
                setPlan((current) => ({
                  ...current,
                  researchQuestions: current.researchQuestions.filter(
                    (_, questionIndex) => questionIndex !== index,
                  ),
                }))
              }
            >
              Delete
            </Button>
          </Space>
        ))}
      </Space>
      <Button
        aria-label="Add question"
        style={{ marginTop: 12 }}
        disabled={disabled || plan.researchQuestions.length >= 12}
        onClick={addQuestion}
      >
        Add question
      </Button>
      {plan.researchQuestions.some((question) => !question.text.trim()) ? (
        <Text type="danger" style={{ display: 'block', marginTop: 8 }}>
          Research questions cannot be blank
        </Text>
      ) : null}

      <Button
        type="primary"
        size="large"
        block
        aria-label={disabled ? 'Approving outline' : 'Approve and start research'}
        loading={disabled}
        disabled={!valid || disabled}
        style={{ marginTop: 24 }}
        onClick={approve}
      >
        {disabled ? 'Approving…' : 'Approve and start research'}
      </Button>
    </Card>
  )
}
