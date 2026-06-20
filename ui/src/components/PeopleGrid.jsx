import { User } from "lucide-react";
import PersonCard from "./PersonCard";
import LoadingSpinner from "./LoadingSpinner";

export default function PeopleGrid({ people, loading, onSelectPerson }) {
  if (loading && people.length === 0) {
    return <LoadingSpinner />;
  }

  if (people.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <User className="w-16 h-16 text-slate-800 mb-4" />
        <h3 className="text-lg font-bold text-slate-400">No people found</h3>
        <p className="text-sm text-slate-600 max-w-sm mt-1">
          Try refining your search query or run extraction on folder.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4 sm:gap-6">
      {people.map((person) => (
        <PersonCard
          key={person.id}
          person={person}
          onClick={() => onSelectPerson(person)}
        />
      ))}
    </div>
  );
}
