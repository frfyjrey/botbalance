import { RouterProvider } from 'react-router-dom';
import { router } from '../routes';

export const AppRouterProvider = () => {
  return <RouterProvider router={router} />;
};
