import { EmptyState } from "@/components/empty-state";

export default function SettingsPage() {
  return (
    <div className="p-4 sm:p-6">
      <EmptyState
        description="Workspace preferences will be available here as they are added."
        title="Settings"
      />
    </div>
  );
}
