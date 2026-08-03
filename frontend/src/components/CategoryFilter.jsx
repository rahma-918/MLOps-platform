import { useState, useEffect } from "react";
import { Tag } from "lucide-react";
import { getCategories } from "../api/client";

export default function CategoryFilter({ value, onChange, domain }) {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    getCategories(domain)
      .then((list) => {
        setCategories(list);
        setLoading(false);
      })
      .catch(() => {
        setCategories([]);
        setLoading(false);
      });
  }, [domain]); // ← RECHARGE quand le domaine change

  return (
    <div className="category-filter">
      <Tag size={14} />
      <select
        value={value || ""}
        onChange={(e) => onChange(e.target.value || null)}
        disabled={loading}
        title="Filtrer par catégorie"
      >
        <option value="">Toutes les catégories</option>
        {categories.map((cat) => (
          <option key={cat.value} value={cat.value}>
            {cat.label}
          </option>
        ))}
      </select>
    </div>
  );
}