// RU: Страница PRO paywall - отображает модальное окно с предложением PRO функций
// EN: PRO paywall page - displays modal dialog with PRO feature offer

import { useNavigate } from 'react-router-dom';
import BeforeAfter from '../../components/Paywall/BeforeAfter';

export default function ProPaywallPage() {
  const navigate = useNavigate();

  const handleClose = () => {
    navigate(-1); // Go back to previous page
  };

  const handlePurchase = () => {
    // TODO: Implement purchase flow
    console.log('Purchase clicked');
    // For now, just close
    handleClose();
  };

  return (
    <BeforeAfter
      onClose={handleClose}
      onPurchase={handlePurchase}
      source="bmi_soft_paywall"
      via="pro_page"
    />
  );
}
