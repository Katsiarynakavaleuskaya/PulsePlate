// RU: Страница PRO paywall - отображает модальное окно с предложением PRO функций
// EN: PRO paywall page - displays modal dialog with PRO feature offer

import { useNavigate } from 'react-router-dom';
import BeforeAfter from '../../components/Paywall/BeforeAfter';
import { purchasePremium } from '../../lib/paywallPurchase';

export default function ProPaywallPage(): JSX.Element {
  const navigate = useNavigate();

  const handleClose = (): void => {
    navigate(-1); // Go back to previous page
  };

  const handlePurchase = async (): Promise<void> => {
    await purchasePremium({ source: "bmi_soft_paywall", via: "pro_page" });
    navigate(-1);
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
