import { TASK_STATES } from '@shared/config/constants';
import type { TaskStatusResponse } from '@shared/config/types';

export type TaskState = typeof TASK_STATES[keyof typeof TASK_STATES];

// Task state utilities
export const getTaskStateColor = (state: string): string => {
  switch (state) {
    case TASK_STATES.SUCCESS:
      return 'text-green-600 bg-green-100';
    case TASK_STATES.FAILURE:
      return 'text-red-600 bg-red-100';
    case TASK_STATES.STARTED:
      return 'text-blue-600 bg-blue-100';
    case TASK_STATES.PENDING:
      return 'text-yellow-600 bg-yellow-100';
    case TASK_STATES.RETRY:
      return 'text-orange-600 bg-orange-100';
    case TASK_STATES.REVOKED:
      return 'text-gray-600 bg-gray-100';
    default:
      return 'text-gray-600 bg-gray-100';
  }
};

export const getTaskStateLabel = (state: string): string => {
  switch (state) {
    case TASK_STATES.SUCCESS:
      return 'Success';
    case TASK_STATES.FAILURE:
      return 'Failed';
    case TASK_STATES.STARTED:
      return 'Running';
    case TASK_STATES.PENDING:
      return 'Pending';
    case TASK_STATES.RETRY:
      return 'Retrying';
    case TASK_STATES.REVOKED:
      return 'Cancelled';
    default:
      return state;
  }
};

export const isTaskComplete = (task: TaskStatusResponse['task']): boolean => {
  return task?.ready || false;
};

export const isTaskSuccessful = (task: TaskStatusResponse['task']): boolean => {
  return task?.successful || false;
};

export const getTaskProgress = (task: TaskStatusResponse['task']): {
  current: number;
  total: number;
  percentage: number;
} => {
  if (!task?.progress) {
    return { current: 0, total: 100, percentage: 0 };
  }

  return {
    current: task.progress.current,
    total: task.progress.total,
    percentage: task.progress.percentage,
  };
};

export const formatTaskResult = (result: any): string => {
  if (typeof result === 'string') {
    return result;
  }
  
  if (typeof result === 'object' && result !== null) {
    return JSON.stringify(result, null, 2);
  }
  
  return String(result);
};
