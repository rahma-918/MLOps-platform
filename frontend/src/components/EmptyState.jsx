export default function EmptyState() {
  return (
    <div className="empty-state">
      <span className="empty-mark">◆</span>
      <h1>Que voulez-vous vérifier aujourd'hui ?</h1>
      <p>
        Ajoutez un document ou posez une question sur votre corpus —
        rapports, contrats, documentation technique — et obtenez une
        réponse sourcée, jamais inventée.
      </p>
      <div className="empty-suggestions">
        <span>« Quelles sont les clauses de résiliation de ce contrat ? »</span>
        <span>« Résume les points clés de cette documentation technique. »</span>
      </div>
    </div>
  );
}