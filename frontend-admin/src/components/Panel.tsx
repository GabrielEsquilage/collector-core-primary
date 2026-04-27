import type { ReactNode } from "react";

type PanelProps = {
  title?: string;
  description?: string;
  children: ReactNode;
};

export function Panel({ title, description, children }: PanelProps) {
  return (
    <section className="panel">
      {title ? (
        <header className="panel-header">
          <div>
            <h3>{title}</h3>
            {description ? <p>{description}</p> : null}
          </div>
        </header>
      ) : null}
      {children}
    </section>
  );
}
