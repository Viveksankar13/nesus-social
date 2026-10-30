"use client";

import * as React from "react";
import { Loader2, Pencil } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/contexts/auth-context";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/components/ui/use-toast";
import type { User, UserUpdateData } from "@/types";

interface EditProfileDialogProps {
  user: User;
}

export function EditProfileDialog({ user }: EditProfileDialogProps) {
  const { refreshUser } = useAuth();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const [open, setOpen] = React.useState(false);
  const [displayName, setDisplayName] = React.useState(user.display_name);
  const [bio, setBio] = React.useState(user.bio || "");
  const [location, setLocation] = React.useState(user.location || "");
  const [website, setWebsite] = React.useState(user.website || "");
  const [avatarUrl, setAvatarUrl] = React.useState(user.avatar_url || "");

  const updateMutation = useMutation({
    mutationFn: (data: UserUpdateData) =>
      apiClient.put<User>("/users/me", data),
    onSuccess: async () => {
      await refreshUser();
      queryClient.invalidateQueries({ queryKey: ["users", "profile", user.username] });
      setOpen(false);
      toast({
        title: "Profile updated",
        description: "Your public profile changes have been saved.",
      });
    },
    onError: (err: Error) => {
      toast({
        title: "Update failed",
        description: err.message,
        variant: "destructive",
      });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateMutation.mutate({
      display_name: displayName.trim(),
      bio: bio.trim() || null,
      location: location.trim() || null,
      website: website.trim() || null,
      avatar_url: avatarUrl.trim() || null,
    });
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="text-xs">
          <Pencil className="mr-1.5 h-3.5 w-3.5" />
          Edit Profile
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Edit Public Profile</DialogTitle>
          <DialogDescription>
            Update how you appear to others on Nexus Social.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 py-2">
          <div className="space-y-1.5">
            <Label htmlFor="display_name">Display Name</Label>
            <Input
              id="display_name"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="bio">Bio</Label>
            <textarea
              id="bio"
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              placeholder="Tell the community about yourself..."
              rows={3}
              maxLength={200}
              className="w-full rounded-md border border-input bg-background p-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
            />
            <span className="text-[10px] text-muted-foreground block text-right">
              {200 - bio.length} chars left
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="location">Location</Label>
              <Input
                id="location"
                placeholder="San Francisco, CA"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="website">Website</Label>
              <Input
                id="website"
                type="url"
                placeholder="https://..."
                value={website}
                onChange={(e) => setWebsite(e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="avatar_url">Avatar Image URL</Label>
            <Input
              id="avatar_url"
              type="url"
              placeholder="https://..."
              value={avatarUrl}
              onChange={(e) => setAvatarUrl(e.target.value)}
            />
          </div>

          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={updateMutation.isPending}>
              {updateMutation.isPending ? (
                <>
                  <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                  Saving...
                </>
              ) : (
                "Save Changes"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
