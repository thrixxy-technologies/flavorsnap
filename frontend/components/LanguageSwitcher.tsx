import { useRouter } from "next/router";
import { useTranslation } from "next-i18next";
import { analytics } from "@/utils/analytics";

const localeLabels: Record<string, string> = {
  en: "English",
  fr: "Français",
  ar: "العربية",
  yo: "Yorùbá",
};

export default function LanguageSwitcher() {
  const router = useRouter();
  const { t } = useTranslation("common");
  const { locale, locales, pathname, asPath, query } = router;

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newLocale = e.target.value;
    
    // Track language change
    analytics.trackLanguageChange(newLocale);
    
    router.push({ pathname, query }, asPath, { locale: newLocale });
  };

  return (
    <div className="flex items-center gap-2">
      <label htmlFor="language-switcher" className="text-sm font-medium">
        {t("select_language")}
      </label>
      <select
        id="language-switcher"
        value={locale}
        onChange={handleChange}
        className=" bg-black text-foreground border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-accent focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 cursor-pointer"
        aria-label={t("select_language")}
      >
        {locales?.map((loc) => (
          <option className="bg-black" key={loc} value={loc}>
            {localeLabels[loc] || loc}
          </option>
        ))}
      </select>
    </div>
  );
}
