import { useCallback, useEffect, useRef, useState } from "react";

/**
 * The documents attached to the active conversation.
 * Works with any api object that implements
 * listDocuments(id), uploadDocument(id, file), deleteDocument(id, docId).
 *
 * Files are uploaded one after another, not in parallel: the backend holds
 * a non-blocking session lock during an upload, so a second simultaneous
 * upload would be rejected with a 409.
 */
export function useDocuments({ api, sessionId, onError }) {
  const [documents, setDocuments] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const activeId = useRef(sessionId);

  useEffect(() => {
    activeId.current = sessionId;
  }, [sessionId]);

  // Reload whenever another conversation is opened.
  useEffect(() => {
    setDocuments([]);

    if (!sessionId) return undefined;

    let cancelled = false;

    api
      .listDocuments(sessionId)
      .then((list) => {
        if (!cancelled) setDocuments(list);
      })
      .catch((requestError) => {
        if (!cancelled) {
          onError?.("Could not load the documents.", requestError);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [api, sessionId, onError]);

  const upload = useCallback(
    async (files) => {
      const targetId = sessionId;
      const list = Array.from(files ?? []);

      if (!targetId || list.length === 0 || isUploading) return;

      setIsUploading(true);

      const failures = [];
      let unreachable = false;

      for (const file of list) {
        try {
          const document = await api.uploadDocument(targetId, file);

          // Ignore the result if the user switched conversations meanwhile.
          if (activeId.current === targetId) {
            setDocuments((current) => [
              ...current.filter((item) => item.id !== document.id),
              document,
            ]);
          }
        } catch (requestError) {
          failures.push(`${file.name}: ${requestError.message}`);

          if (requestError.status === 0) {
            unreachable = true;
            break;
          }
        }
      }

      setIsUploading(false);

      if (failures.length > 0) {
        onError?.("Could not add the document.", {
          message: failures.join(" "),
          status: unreachable ? 0 : 422,
        });
      }
    },
    [api, sessionId, isUploading, onError],
  );

  const remove = useCallback(
    async (documentId) => {
      const targetId = sessionId;

      try {
        await api.deleteDocument(targetId, documentId);

        if (activeId.current === targetId) {
          setDocuments((current) =>
            current.filter((item) => item.id !== documentId),
          );
        }
      } catch (requestError) {
        onError?.("Could not remove the document.", requestError);
      }
    },
    [api, sessionId, onError],
  );

  return { documents, isUploading, upload, remove };
}