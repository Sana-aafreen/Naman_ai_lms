export interface Module {
  id: string;
  title: string;
  topic: string;
  overview?: string;
  key_concepts?: { title: string; description: string }[];
  examples?: string[];
  practice_questions?: any[];
  mini_project?: string;
  summary?: string;
  content?: any;
  created_at?: string;
}

export interface Department {
  id: string;
  name: string;
}

export const DEPARTMENT_LABELS: Record<string, string> = {
  Finance: 'Finance',
  Sales: 'Sales',
  HR: 'Human Resources',
  Operations: 'Operations',
  Legal: 'Legal',
  General: 'General',
};
