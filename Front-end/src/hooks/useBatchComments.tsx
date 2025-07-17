
import { useState, useEffect, useCallback } from 'react';
import { supabase } from '@/integrations/api/client';
import { useAuth } from '@/hooks/useAuth';
import { useUserProfiles } from '@/hooks/useUserProfiles';
import { getMonthDateRange } from '@/utils/dateUtils';

export interface BatchComment {
  id: string;
  content: string;
  created_at: string;
  user_id: string;
  user_name: string;
  application_id: string;
}

export const useBatchComments = (selectedMonth?: string | null) => {
  const { user } = useAuth();
  const { getUserName, fetchProfiles } = useUserProfiles();
  const [comments, setComments] = useState<Record<string, BatchComment[]>>({});
  const [loading, setLoading] = useState(false);

  const fetchBatchComments = useCallback(async (applicationIds: string[]): Promise<Record<string, BatchComment[]>> => {
    if (!user || !applicationIds.length) return {};

    setLoading(true);
    
    try {
      console.log('=== BATCH FETCHING COMMENTS ===');
      console.log('Application IDs:', applicationIds.slice(0, 5), '... and', Math.max(0, applicationIds.length - 5), 'more');
      console.log('Selected Month:', selectedMonth);

      // Build query for batch comment fetching - fetch ALL comments for applications
      const query = supabase
        .from('comments')
        .select('*')
        .in('application_id', applicationIds)
        .order('created_at', { ascending: false })
        .limit(200); // Increased limit for better coverage across applications

      console.log('Fetching all comments for applications (no date filtering)');

      const { data: commentsData, error: commentsError } = await query;

      if (commentsError) {
        console.error('Error batch fetching comments:', commentsError);
        return {};
      }

      if (!commentsData || commentsData.length === 0) {
        console.log('No comments found for applications');
        setComments({});
        return {};
      }

      console.log('Raw batch comments data:', commentsData.length, 'comments');

      // Get unique user IDs for profile fetching
      const userIds = [...new Set(commentsData.map(comment => comment.user_id))];
      console.log('Fetching profiles for user IDs:', userIds);

      // Fetch user profiles and wait for them to be cached
      console.log('Fetching profiles for user IDs:', userIds);
      await fetchProfiles(userIds);
      console.log('Profiles fetched, waiting for cache...');
      // Give more time for profile resolution
      await new Promise(resolve => setTimeout(resolve, 200));

      // Group comments by application_id and limit to 2 most recent per application
      const groupedComments: Record<string, BatchComment[]> = {};
      
      console.log('Processing comments for user name resolution...');
      commentsData.forEach((comment, index) => {
        const userName = getUserName(comment.user_id, comment.user_email);
        console.log(`Comment ${index + 1}: User ID: ${comment.user_id}, Resolved name: "${userName}", Email: ${comment.user_email}`);
        
        if (!groupedComments[comment.application_id]) {
          groupedComments[comment.application_id] = [];
        }
        
        // Only keep top 2 comments per application for main page display
        if (groupedComments[comment.application_id].length < 2) {
          groupedComments[comment.application_id].push({
            ...comment,
            user_name: userName
          });
        }
      });

      console.log('=== FINAL COMMENTS SUMMARY ===');
      console.log('Applications with comments:', Object.keys(groupedComments).length);
      Object.entries(groupedComments).forEach(([appId, comments]) => {
        console.log(`${appId}: ${comments.length} comments`);
        comments.forEach((comment, i) => {
          console.log(`  Comment ${i + 1}: "${comment.content.substring(0, 50)}..." by ${comment.user_name}`);
        });
      });
      
      setComments(groupedComments);
      return groupedComments;
    } catch (error) {
      console.error('Exception in batch fetchComments:', error);
      return {};
    } finally {
      setLoading(false);
    }
  }, [user, fetchProfiles, getUserName, selectedMonth]);

  // Clear comments when selectedMonth changes
  useEffect(() => {
    setComments({});
  }, [selectedMonth]);

  return {
    comments,
    loading,
    fetchBatchComments
  };
};
