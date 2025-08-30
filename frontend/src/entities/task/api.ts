import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@shared/lib/api';
import { QUERY_KEYS } from '@shared/config/constants';
import type { TaskResponse, TaskStatusResponse } from '@shared/config/types';

// Task creation mutations
export const useCreateEchoTask = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ message, delay = 0 }: { message: string; delay?: number }) =>
      apiClient.createEchoTask(message, delay),
    onSuccess: (data: TaskResponse) => {
      console.log('Echo task created:', data);
      // Invalidate tasks query to refetch
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.TASKS] });
    },
  });
};

export const useCreateHeartbeatTask = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => apiClient.createHeartbeatTask(),
    onSuccess: (data: TaskResponse) => {
      console.log('Heartbeat task created:', data);
      // Invalidate tasks query to refetch
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.TASKS] });
    },
  });
};

// Task status query
export const useTaskStatus = (
  taskId: string | null,
  options?: {
    enabled?: boolean;
    refetchInterval?: number;
  },
) => {
  return useQuery({
    queryKey: [QUERY_KEYS.TASK_STATUS, taskId],
    queryFn: () => apiClient.getTaskStatus(taskId!),
    enabled: !!taskId && options?.enabled !== false,
    refetchInterval: query => {
      // Stop polling if task is complete
      const data = query.state.data as TaskStatusResponse | undefined;
      if (data?.task?.ready) {
        return false;
      }
      return options?.refetchInterval ?? 1000; // Poll every second by default
    },
    refetchIntervalInBackground: false,
  });
};

// Helper hook for task polling with automatic stop
export const useTaskPolling = (taskId: string | null) => {
  const { data, isLoading, error } = useTaskStatus(taskId, {
    refetchInterval: 1000,
  });

  const isComplete = (data as TaskStatusResponse)?.task?.ready || false;
  const isSuccess = (data as TaskStatusResponse)?.task?.successful || false;
  const hasError =
    (data as TaskStatusResponse)?.status === 'error' ||
    (data as TaskStatusResponse)?.task?.state === 'FAILURE';

  return {
    task: (data as TaskStatusResponse)?.task,
    isLoading,
    error,
    isComplete,
    isSuccess,
    hasError,
  };
};
