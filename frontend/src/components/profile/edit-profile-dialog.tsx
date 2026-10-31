"use client";

import * as React from "react";
import { Camera, Loader2, Pencil } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/contexts/auth-context";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
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
import { getInitials } from "@/lib/utils";
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
  const [usn, setUsn] = React.useState(user.usn || "");
  const [bio, setBio] = React.useState(user.bio || "");
  const [location, setLocation] = React.useState(user.location || "");
  const [website, setWebsite] = React.useState(user.website || "");
  const [avatarUrl, setAvatarUrl] = React.useState(user.avatar_url || "");
  const [isUploadingAvatar, setIsUploadingAvatar] = React.useState(false);
  const avatarFileRef = React.useRef<HTMLInputElement>(null);

  const handleAvatarFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
      toast({
        title: "File too large",
        description: "Avatar image must be under 5MB.",
        variant: "destructive",
      });
      return;
    }

    setIsUploadingAvatar(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const updatedUser = await apiClient.post<User>("/media/avatar", formData);
      setAvatarUrl(updatedUser.avatar_url || "");
      await refreshUser();
      queryClient.invalidateQueries({ queryKey: ["users", "profile", user.username] });
      toast({
        title: "Avatar updated!",
        description: "Your new profile picture is active.",
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to upload avatar";
      toast({
        title: "Upload failed",
        description: msg,
        variant: "destructive",
      });
    } finally {
      setIsUploadingAvatar(false);
      if (avatarFileRef.current) avatarFileRef.current.value = "";
    }
  };

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
      usn: usn.trim().toUpperCase() || null,
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
            <div className="flex items-center justify-between">
              <Label htmlFor="usn">Student USN / College ID</Label>
              <span className="text-[10px] text-muted-foreground">e.g. 1MS21CS001</span>
            </div>
            <Input
              id="usn"
              placeholder="e.g. 1MS21CS001"
              value={usn}
              onChange={(e) => setUsn(e.target.value.toUpperCase())}
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

          <div className="space-y-2 pt-1 border-t">
            <Label>Profile Picture</Label>
            <div className="flex items-center gap-4">
              <Avatar className="h-16 w-16 border-2 border-primary/20 shadow-sm">
                <AvatarImage src={avatarUrl || `https://avatar.vercel.sh/${user.username}`} />
                <AvatarFallback>{getInitials(displayName || user.display_name)}</AvatarFallback>
              </Avatar>

              <div className="flex-1 space-y-2">
                <input
                  ref={avatarFileRef}
                  type="file"
                  accept="image/png,image/jpeg,image/webp,image/gif"
                  className="hidden"
                  onChange={handleAvatarFileChange}
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="gap-1.5 text-xs"
                  onClick={() => avatarFileRef.current?.click()}
                  disabled={isUploadingAvatar}
                >
                  {isUploadingAvatar ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      Uploading...
                    </>
                  ) : (
                    <>
                      <Camera className="h-3.5 w-3.5" />
                      Upload Photo
                    </>
                  )}
                </Button>
                <p className="text-[11px] text-muted-foreground">
                  JPG, PNG, WebP or GIF. Max 5MB.
                </p>
              </div>
            </div>

            <div className="pt-1">
              <Label htmlFor="avatar_url" className="text-xs text-muted-foreground">Or Avatar Image URL</Label>
              <Input
                id="avatar_url"
                type="url"
                placeholder="https://..."
                value={avatarUrl}
                onChange={(e) => setAvatarUrl(e.target.value)}
                className="h-8 text-xs mt-1"
              />
            </div>
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
