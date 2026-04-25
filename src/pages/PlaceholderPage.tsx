import { Layout } from "@/components/Layout";
import { Pill } from "@/components/Pill";

interface PlaceholderPageProps {
  title: string;
  path: string;
}

/** Empty foundation page used by every route until screens are built. */
const PlaceholderPage = ({ title, path }: PlaceholderPageProps) => {
  return (
    <Layout>
      <div className="flex-1 flex flex-col items-center justify-center px-6 text-center gap-3">
        <Pill tone="blush">Foundation</Pill>
        <h1 className="text-h1 text-navy">{title}</h1>
        <p className="text-body text-slate">{path}</p>
      </div>
    </Layout>
  );
};

export default PlaceholderPage;
