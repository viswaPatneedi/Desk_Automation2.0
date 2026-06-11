import { useSelector } from 'react-redux';
import { selectModals } from '@store/slices/modalSlice';

// Modal Components - will be dynamically imported
const modalComponents = {
  'login': () => import('./auth/LoginModal'),
  'device-add': () => import('./device/DeviceAddModal'),
  'device-edit': () => import('./device/DeviceEditModal'),
  'job-create': () => import('./job/JobCreateModal'),
  'results-view': () => import('./results/ResultsViewModal'),
};

export default function ModalContainer() {
  const modals = useSelector(selectModals);

  return (
    <div className="modal-container">
      {Object.entries(modals).map(([id, modal]) => {
        const ModalComponent = modalComponents[modal.type]?.();
        
        if (!ModalComponent) {
          return null;
        }

        return (
          <ModalComponent
            key={id}
            id={id}
            data={modal.data}
          />
        );
      })}
    </div>
  );
}
