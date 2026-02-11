import DonkitIcon from '../../assets/donkit-icon-round.svg';

interface HeaderProps {
  provider?: string;
  model?: string | null;
}

export default function Header({ provider, model }: HeaderProps) {
  return (
    <header
      style={{
        padding: `var(--space-xs) var(--page-padding-hor)`,
        borderBottom: '1px solid var(--color-border)',
        backgroundColor: 'var(--color-bg)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}
    >
      <div className="flex items-center" style={{ gap: 'var(--space-s)' }}>
        <img
          src={DonkitIcon}
          alt="Donkit"
          width={32}
          height={32}
          style={{ borderRadius: 'var(--space-s)' }}
        />
        <p className="p2" style={{ margin: 0, color: 'var(--color-txt-icon-1)' }}>
          <span style={{ fontWeight: 600 }}>RAGOps</span>
          <span style={{ marginLeft: 'var(--space-s)', fontWeight: 300 }}>
            AI-Powered RAG Pipeline Builder
          </span>
        </p>
      </div>
      {provider && (
        <div className="p2">
          <span style={{ fontWeight: 500 }}>{provider}</span>
          {model && <span style={{ marginLeft: 'var(--space-xs)', color: 'var(--color-txt-icon-2)' }}>/ {model}</span>}
        </div>
      )}
    </header>
  );
}
