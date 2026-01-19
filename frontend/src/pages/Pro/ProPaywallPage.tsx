// RU: Страница PRO paywall - отображает модальное окно с предложением PRO функций
// EN: PRO paywall page - displays modal dialog with PRO feature offer

import { useNavigate } from 'react-router-dom';
import BeforeAfter from '../../components/Paywall/BeforeAfter';

export default function ProPaywallPage(): JSX.Element {
  const navigate = useNavigate();

  const handleClose = (): void => {
    navigate(-1); // Go back to previous page
  };

  return (
    <BeforeAfter
      onClose={handleClose}
      purchaseDisabled
      purchaseLabel="Coming soon"
      source="bmi_soft_paywall"
      via="pro_page"
    />
  );
}
