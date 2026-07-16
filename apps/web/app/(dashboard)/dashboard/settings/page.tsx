import { EmptyState } from "@/components/empty-state";

export default function SettingsPage() {
  return (
    <main className="mx-auto max-w-4xl p-4 pb-24 sm:p-6 md:pb-8 lg:p-8">
      <EmptyState
        description="Workspace preferences will be available here as they are added."
        title="Settings"
      />
    </main>
  );
}
